"""
Fundamental Analysis Service
"""
import math
import yfinance as yf
import logging

logger = logging.getLogger(__name__)


def get_fundamentals(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        pe_ratio = info.get("trailingPE") or info.get("forwardPE")
        debt_to_equity = info.get("debtToEquity")
        revenue_growth = info.get("revenueGrowth")
        eps = info.get("trailingEps")
        bvps = info.get("bookValue")
        current_price = info.get("currentPrice") or info.get("previousClose")
        market_cap = info.get("marketCap")
        dividend_yield = info.get("dividendYield")
        roe = info.get("returnOnEquity")
        profit_margin = info.get("profitMargins")
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        
        graham_value = None
        if eps and bvps and eps > 0 and bvps > 0:
            graham_value = round(math.sqrt(22.5 * eps * bvps), 2)
        
        valuation = "N/A"
        if graham_value and current_price:
            ratio = current_price / graham_value
            if ratio < 0.8:
                valuation = "Undervalued"
            elif ratio < 1.2:
                valuation = "Fair Value"
            else:
                valuation = "Overvalued"
        
        fund_score = 50
        if pe_ratio:
            if pe_ratio < 15:
                fund_score += 20
            elif pe_ratio < 25:
                fund_score += 10
            elif pe_ratio > 40:
                fund_score -= 15
        
        if debt_to_equity:
            if debt_to_equity < 50:
                fund_score += 15
            elif debt_to_equity < 100:
                fund_score += 5
            else:
                fund_score -= 10
        
        if revenue_growth:
            if revenue_growth > 0.15:
                fund_score += 15
            elif revenue_growth > 0.05:
                fund_score += 5
            elif revenue_growth < 0:
                fund_score -= 10
        
        if graham_value and current_price:
            if current_price < graham_value:
                fund_score += 10
            elif current_price > graham_value * 1.5:
                fund_score -= 5
        
        fund_score = max(0, min(100, fund_score))
        
        return {
            "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
            "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
            "revenue_growth": round(revenue_growth * 100, 2) if revenue_growth else None,
            "eps": round(eps, 2) if eps else None,
            "bvps": round(bvps, 2) if bvps else None,
            "graham_value": graham_value,
            "current_price": round(current_price, 2) if current_price else None,
            "market_cap": market_cap,
            "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield else None,
            "roe": round(roe * 100, 2) if roe else None,
            "profit_margin": round(profit_margin * 100, 2) if profit_margin else None,
            "sector": sector,
            "industry": industry,
            "valuation": valuation,
            "fundamental_score": fund_score,
        }
    except Exception as e:
        logger.error(f"Error getting fundamentals for {symbol}: {e}")
        return {
            "error": str(e),
            "fundamental_score": 50,
            "pe_ratio": None,
            "debt_to_equity": None,
            "revenue_growth": None,
            "eps": None,
            "bvps": None,
            "graham_value": None,
            "current_price": None,
            "valuation": "N/A",
            "sector": "N/A",
            "industry": "N/A",
        }
